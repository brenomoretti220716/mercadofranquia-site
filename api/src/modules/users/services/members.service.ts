import {
  BadRequestException,
  ConflictException,
  ForbiddenException,
  Injectable,
  NotFoundException,
} from '@nestjs/common';
import { Prisma, Role, User } from '@prisma/client';
import { PrismaService } from '../../database/prisma.service';
import { EmailService } from '../../email/email.service';
import {
  UpdateUserBasicInfoDto,
  UpdateUserProfileDto,
} from '../schemas/update-user.schema';

interface UpdateFranchiseeUserDto
  extends UpdateUserBasicInfoDto,
    UpdateUserProfileDto {
  city?: string;
  franchiseeOf?: string[];
}

interface CurrentUserData {
  id: string;
  name: string;
  role: Role;
  email: string;
}

@Injectable()
export class MembersService {
  constructor(
    private prisma: PrismaService,
    private emailService: EmailService,
  ) {}

  private async validateFranchises(franchiseeOf?: string[]): Promise<void> {
    if (!franchiseeOf || franchiseeOf.length === 0) {
      return;
    }

    const existingFranchises = await this.prisma.franchise.findMany({
      where: {
        id: { in: franchiseeOf },
      },
      select: {
        id: true,
        name: true,
      },
    });

    const foundFranchiseIds = existingFranchises.map((f) => f.id);
    const notFoundFranchises = franchiseeOf.filter(
      (id) => !foundFranchiseIds.includes(id),
    );

    if (notFoundFranchises.length > 0) {
      throw new BadRequestException(
        `Franchises with IDs ${notFoundFranchises.join(', ')} do not exist`,
      );
    }
  }

  async update(
    id: string,
    userData: UpdateFranchiseeUserDto,
    currentUserId: string,
    currentUserRole: Role,
    currentUser?: CurrentUserData,
  ): Promise<Omit<User, 'password'>> {
    const uuidRegex =
      /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(id)) {
      throw new BadRequestException('Invalid user ID format');
    }

    const existingUser = await this.prisma.user.findUnique({
      where: { id },
      include: {
        franchiseeOf: true,
        profile: true,
      },
    });

    if (!existingUser) {
      throw new NotFoundException('User not found');
    }

    if (currentUserId !== id && currentUserRole !== Role.ADMIN) {
      throw new ForbiddenException('You can only update your own profile');
    }

    if (userData.phone && userData.phone !== existingUser.phone) {
      const phoneExists = await this.findByPhone(userData.phone);
      if (phoneExists) {
        throw new ConflictException('Phone already in use by another user');
      }
    }

    if (userData.franchiseeOf !== undefined) {
      await this.validateFranchises(userData.franchiseeOf);
    }

    const user = await this.prisma.$transaction(async (tx) => {
      const updateData: Prisma.UserUpdateInput = {
        ...(userData.name !== undefined && { name: userData.name }),
        ...(userData.phone !== undefined && { phone: userData.phone }),
      };

      if (currentUserRole === Role.ADMIN) {
        if (userData.isActive !== undefined) {
          updateData.isActive = userData.isActive;
        }
      } else {
        if (userData.isActive !== undefined) {
          throw new ForbiddenException(
            'Only administrators can change account status',
          );
        }
      }

      const updatedUser = await tx.user.update({
        where: { id },
        data: updateData,
      });

      if (existingUser.profile) {
        const profileUpdateData: Prisma.UserProfileUpdateInput = {};

        if (userData.city !== undefined) {
          profileUpdateData.city = userData.city;
        }
        if (userData.interestSectors !== undefined) {
          profileUpdateData.interestSectors = userData.interestSectors;
        }
        if (userData.interestRegion !== undefined) {
          profileUpdateData.interestRegion = userData.interestRegion;
        }
        if (userData.investmentRange !== undefined) {
          profileUpdateData.investmentRange = userData.investmentRange;
        }

        if (Object.keys(profileUpdateData).length > 0) {
          await tx.userProfile.update({
            where: { userId: id },
            data: profileUpdateData,
          });
        }

        if (userData.role !== undefined) {
          await tx.user.update({
            where: { id },
            data: { role: userData.role },
          });
        }

        const finalRole = userData.role || existingUser.role;

        if (
          finalRole === Role.FRANCHISEE &&
          userData.franchiseeOf !== undefined
        ) {
          await tx.user.update({
            where: { id },
            data: {
              franchiseeOf: {
                set: [],
              },
            },
          });

          if (userData.franchiseeOf.length > 0) {
            await tx.user.update({
              where: { id },
              data: {
                franchiseeOf: {
                  connect: userData.franchiseeOf.map((franchiseId) => ({
                    id: franchiseId,
                  })),
                },
              },
            });
          }
        } else if (finalRole !== Role.FRANCHISEE) {
          await tx.user.update({
            where: { id },
            data: { franchiseeOf: { set: [] } },
          });
        }
      }

      return updatedUser;
    });

    if (currentUser && currentUserRole === Role.ADMIN && currentUserId !== id) {
      try {
        await this.emailService.sendUserUpdateNotification({
          userEmail: user.email,
          userName: user.name,
        });
      } catch (error) {
        console.error('Failed to send email notification:', error);
      }
    }

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { password, ...result } = user;
    return result;
  }

  async findMembersPaginated({
    page = 1,
    limit = 10,
    search = '',
  }: {
    page?: number;
    limit?: number;
    search?: string;
  }) {
    const skip = (page - 1) * limit;
    const where: Prisma.UserWhereInput = {
      role: {
        in: [Role.FRANCHISEE, Role.CANDIDATE, Role.ENTHUSIAST, Role.MEMBER],
      },
    };
    if (search && search.trim()) {
      const lower = search.toLowerCase();
      where.OR = [
        { name: { contains: lower } },
        { email: { contains: lower } },
      ];
    }
    const [data, total, totalActive, totalInactive] = await Promise.all([
      this.prisma.user.findMany({
        where,
        skip,
        take: limit,
        include: {
          franchiseeOf: {
            select: {
              id: true,
              name: true,
              segment: true,
              subsegment: true,
              minimumInvestment: true,
              maximumInvestment: true,
              totalUnits: true,
              headquarterState: true,
            },
          },
          profile: true,
        },
      }),
      this.prisma.user.count({ where }),
      this.prisma.user.count({
        where: {
          role: { in: [Role.FRANCHISEE, Role.CANDIDATE, Role.ENTHUSIAST] },
          isActive: true,
        },
      }),
      this.prisma.user.count({
        where: {
          role: { in: [Role.FRANCHISEE, Role.CANDIDATE, Role.ENTHUSIAST] },
          isActive: false,
        },
      }),
    ]);
    return {
      data,
      total,
      totalActive,
      totalInactive,
      page,
      lastPage: Math.ceil(total / limit),
    };
  }

  async findByEmail(email: string): Promise<User | null> {
    return this.prisma.user.findUnique({
      where: { email },
    });
  }

  async findByPhone(phone: string): Promise<User | null> {
    return this.prisma.user.findUnique({
      where: { phone },
    });
  }

  async findByCpf(cpf: string): Promise<User | null> {
    return this.prisma.user.findUnique({
      where: { cpf },
    });
  }

  async findById(id: string): Promise<Omit<User, 'password'> | null> {
    const user = await this.prisma.user.findUnique({
      where: { id },
      include: {
        franchiseeOf: {
          select: {
            id: true,
            name: true,
            segment: true,
            subsegment: true,
            minimumInvestment: true,
            maximumInvestment: true,
            totalUnits: true,
            headquarterState: true,
          },
        },
        profile: true,
      },
    });

    if (!user) {
      return null;
    }

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { password, ...result } = user;
    return result;
  }
}
